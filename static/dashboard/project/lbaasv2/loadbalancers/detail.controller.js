/*
 * Copyright 2015 IBM Corp.
 *
 * Licensed under the Apache License, Version 2.0 (the 'License');
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an 'AS IS' BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
(function() {
  'use strict';

  angular
    .module('horizon.dashboard.project.lbaasv2.loadbalancers')
    .controller('LoadBalancerDetailController', LoadBalancerDetailController);

  LoadBalancerDetailController.$inject = [
    'horizon.app.core.openstack-service-api.lbaasv2',
    'horizon.dashboard.project.lbaasv2.loadbalancers.actions.rowActions',
    'horizon.dashboard.project.lbaasv2.loadbalancers.service',
    '$routeParams',
    '$window',
    '$scope'
  ];

  /**
   * @ngdoc controller
   * @name LoadBalancerDetailController
   *
   * @description
   * Controller for the LBaaS v2 load balancers detail page.
   *
   * @param api The LBaaS v2 API service.
   * @param rowActions The load balancer row actions service.
   * @param loadBalancersService The LBaaS v2 load balancers service.
   * @param $routeParams The angular $routeParams service.
   * @param $window Angular's reference to the browser window object.
   * @param $scope The angular scope object.
   * @returns undefined
   */

  function LoadBalancerDetailController(
    api, rowActions, loadBalancersService, $routeParams, $window, $scope
  ) {
    var ctrl = this;
    $scope.isShow = true;
    ctrl.pools = [];
    ctrl.actions = rowActions.actions;
    ctrl.operatingStatus = loadBalancersService.operatingStatus;
    ctrl.provisioningStatus = loadBalancersService.provisioningStatus;
    ctrl.listenersTabActive = $window.listenersTabActive;

    $scope.actions = {

    }

    init();

    ////////////////////////////////

    function init() {
        api.getLoadBalancer($routeParams.loadbalancerId, true).success(success);
        api.getListeners($routeParams.loadbalancerId, true).success(get_listeners);
    }
    function success(response) {
        ctrl.loadbalancer = response;
    }
    function get_listeners(response) {
        ctrl.listeners = response.items;
        for(var i in response.items ){
            api.getPool(response.items[i].default_pool_id).success(set_pool(response.items[i],'pool'));

    }}
    function set_pool(listener_item,property) {
        return angular.bind(listener_item, function setProp(property, value) {
            listener_item[property] = value;
            for (var i in listener_item[property].members){
                api.getMember(listener_item[property].id,listener_item[property].members[i].id).success(set_member(listener_item[property],'member'));
            }
            console.log(listener_item[property])
    }, property);}
    function set_member(pool,property) {
        return angular.bind(pool,function setProp(property,value) {if(pool[property]==null){pool[property] = [];pool[property].push(value);}else {pool[property].push(value);} console.log(pool.property) },property);
    }

    $scope.$watch(function() {
        return ctrl.listenersTabActive;
    },
    function(active) {
        $window.listenersTabActive = active;
    });

  }

})();
