function success(response) {
    ctrl.loadbalancer = response;
    console.log(response.listeners);
    for (var i in response.listeners) {
        console.log(response.listeners[i].id)
    };
    api.getListener(response.listeners[i].id, true).success(success_lis);
}
function set(property) {
    return angular.bind(null,
    function setProp(property, value) {
        ctrl[property] = value;
    },
    property);
}
function success_lis(response) {
    ctrl.listener = response;
    console.log(response.pool);
    ctrl.pool = response.pool
}