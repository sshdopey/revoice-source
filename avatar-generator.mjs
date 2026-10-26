import { Style, Avatar } from '@dicebear/core';
import definition from '@dicebear/styles/waves.json' with { type: 'json' };
const style = new Style(definition);
export function createWave(seed) {
    return new Avatar(style, { seed, scale: 1.4, tags: ['animation'] }).toString();
}
