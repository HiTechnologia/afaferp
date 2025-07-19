/** @odoo-module **/

import { registry } from '@web/core/registry';
import { rpc } from "@web/core/network/rpc";
import { loadBundle } from "@web/core/assets";
import { formView } from '@web/views/form/form_view';
import { FormRenderer } from '@web/views/form/form_renderer';
import { loadJS, loadCSS } from "@web/core/assets";

const { 
    Component,
    onWillStart,
    useEffect,
    useRef,
    onMounted,
    useState,
    toRaw
} = owl;

export class TraccarFormRenderer extends FormRenderer {
    setup() {
        super.setup();
        var self = this;
        this.olmap = null;
        
        useEffect(
            () => {
                self.olmap = new ol.Map({
                    layers: [
                        new ol.layer.Tile({
                            source: new ol.source.OSM(),
                        }),
                    ],
                    target: document.getElementById("o_traccar_map_view"),
                    view: new ol.View({
                        center: ol.proj.fromLonLat([0, 0]),
                        zoom: 4,
                    }),
                });
                self.olmap.updateSize();
                if (self.olmap){
                    self.addLayerVector();
                    self.addLayerpopup();
                }
            },
            () => []
        );
        useEffect(() => {
            if (self.olmap.values_.target.getAttribute('show_route_trip') == 'true') {
                self.addRoutePoints();
            }
            if (self.olmap.values_.target.getAttribute('show_current_position') == 'true') {
                self.addCurrentPosition();
            }
        });

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        Promise.all([
            await loadJS("/fleet_traccar_tracking/static/src/js/lib/ol-10.0.0/ol.js"),
            await loadCSS("/fleet_traccar_tracking/static/src/js/lib/ol-10.0.0/ol.css"),
            await loadCSS("/fleet_traccar_tracking/static/src/css/ol_style.css"),
        ]);
        // await loadBundle({
        //     cssLibs: [
        //         '/fleet_traccar_tracking/static/src/js/lib/ol-7.1.0/ol.css',
        //         '/fleet_traccar_tracking/static/src/css/ol_style.css',
        //     ],
        //     jsLibs: [
        //         '/fleet_traccar_tracking/static/src/js/lib/ol-7.1.0/ol.js',
        //     ],
        // });
    }

    addLayerpopup(){
        var self = this;
        var target = document.getElementById("popup");
        if (target){
            var popup = new ol.Overlay({
                element: target,
                autoPan: true,
                autoPanAnimation: {
                    duration: 250
                }
            });
            self.olmap.addOverlay(popup);
            self.olmap.on('pointermove', function (evt) {
                if (evt.dragging) {
                    return;
                }
                if (self.olmap.forEachFeatureAtPixel != undefined ){
                    var feature = self.olmap.forEachFeatureAtPixel(evt.pixel, function (feat, layer) {
                        return feat;
                    });
                    if (feature && feature.get('type') == 'Point') {
                        var coordinate = evt.coordinate;
                        target.innerHTML = feature.get('desc');
                        popup.setPosition(coordinate);
                    }
                    else {
                        popup.setPosition(undefined);                    
                    }
                }                
            });
        }
    }

    addLayerVector(){
        var self = this;        
        if (!cancelIdleCallback.vectorSource) {
            self.vectorSource = new ol.source.Vector();
        }
        if (!self.vectorLayer) {
            self.vectorLayer = new ol.layer.Vector({
                source: self.vectorSource,
                name: 'vectorSource',
                style: new ol.style.Style({
                    fill: new ol.style.Fill({
                        color: 'rgb(255 235 59 / 62%)',
                    }),
                    stroke: new ol.style.Stroke({
                        color: '#ffc107',
                        width: 2,
                    }),
                    image: new ol.style.Circle({
                        radius: 7,
                        fill: new ol.style.Fill({
                            color: '#ffc107',
                        }),
                    }),
                }),
            });
            self.olmap.addLayer(self.vectorLayer);
        }
    }

    addRoutePoints(){
        var self = this;
        self.vectorSource.clear();
        if (self.props.record.data.src_latitude && self.props.record.data.src_longitude) {
            var data = self.props.record.data;
            var source = {
                long: data.src_longitude,
                lat: data.src_latitude,
                coords: data.src_longitude + ',' + data.src_latitude
            };
            var destination = {
                long: data.dst_longitude,
                lat: data.dst_latitude,
                coords: data.dst_longitude + ',' + data.dst_latitude
            };

            var url_osrm_route = '//router.project-osrm.org/route/v1/driving/';
            var url = `${url_osrm_route}${source.coords};${destination.coords}`;

            fetch(url).then(function (response) {
                return response.json();
            }).then(function (json) {
                self.vectorSource.addFeature(self.addMarker(source));
                self.vectorSource.addFeature(self.addMarker(destination));
                if(json.code == 'Ok') {
                    self.vectorSource.addFeature(self.addPolyline(json));  
                    self.olmap.getView().fit(self.vectorSource.getExtent(), self.olmap.getSize(), { duration: 100, maxZoom: 6 });
                }                
            });
        }
        
    }

    addMarker(coords) {
        var iconStyle = new ol.style.Style({
            image: new ol.style.Icon({
                scale: .2,
                crossOrigin: 'anonymous',
                src: "/fleet_traccar_tracking/static/src/img/marker.png",
                opacity: 1,
            })
        });
        var desc = '<pre><span style="font-weight: bold;">Waypoint Details</span>' + '<br>' + 'Latitude : ' + coords.lat + '<br>Longitude: ' + coords.long + '</pre>';
        var marker = new ol.Feature({
          geometry: new ol.geom.Point(ol.proj.fromLonLat([coords.long, coords.lat])),
          desc: desc,
          type: 'Point',
        });
        marker.setStyle(iconStyle);
        return marker
    }

    addPolyline(json){
        var routeStyle = {
            route: new ol.style.Style({
              stroke: new ol.style.Stroke({
                width: 4, color: [40, 40, 40, 0.8]
              })
            })
        };
        var geometry = json.routes[0].geometry;
        var format = new ol.format.Polyline({
            factor: 1e5
        }).readGeometry(geometry, {
            dataProjection: 'EPSG:4326',
            featureProjection: 'EPSG:3857',
        });
        
        var polyline = new ol.Feature({
            type: 'route',
            geometry: format
        });
        polyline.setStyle(routeStyle.route);
        return polyline;
    }

    addCurrentPosition(){
        var self = this;
        self.vectorSource.clear();
        if (self.props.record.data.latitude && self.props.record.data.longitude) {
            var data = self.props.record.data;

            var iconStyle = new ol.style.Style({
                image: new ol.style.Icon({
                    scale: .2,
                    crossOrigin: 'anonymous',
                    src: "/fleet_traccar_tracking/static/src/img/marker.png",
                    opacity: 1,
                })
            });
            
            var marker = new ol.Feature({
              geometry: new ol.geom.Point(ol.proj.fromLonLat([data.longitude, data.latitude])),
              type: 'Position',
            });

            marker.setStyle(iconStyle);
            
            self.vectorSource.addFeature(marker);
            self.olmap.getView().fit(self.vectorSource.getExtent(), { duration: 100, maxZoom: 6 });
        }        
    }
}

registry.category('views').add('traccar_map_form', {
    ...formView,
    Renderer: TraccarFormRenderer,
});