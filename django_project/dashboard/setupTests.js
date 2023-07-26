export const mockMapOn = jest.fn();
export const mockMapRemove = jest.fn();

jest.mock('mapbox-gl', () => ({
    Map: function () {
        this.on = mockMapOn;
        this.remove = mockMapRemove;
    }
}));
