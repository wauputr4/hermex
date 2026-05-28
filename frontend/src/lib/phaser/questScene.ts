import Phaser from 'phaser';

export function mountQuestScene(target: HTMLElement, label = 'Reflection Quest') {
  const config: Phaser.Types.Core.GameConfig = {
    type: Phaser.AUTO,
    width: 420,
    height: 220,
    parent: target,
    backgroundColor: '#10251f',
    scene: {
      create() {
        const scene = this as Phaser.Scene;
        scene.add.text(28, 32, 'Hermex Quest', {
          fontFamily: 'Georgia',
          fontSize: '28px',
          color: '#f7e6b1'
        });
        scene.add.text(28, 82, label, {
          fontFamily: 'Georgia',
          fontSize: '18px',
          color: '#d7ffd9'
        });
        scene.add.circle(338, 116, 34, 0xf2c14e, 0.9);
        scene.tweens.add({
          targets: scene.children.list.at(-1),
          y: 96,
          duration: 1200,
          yoyo: true,
          repeat: -1,
          ease: 'Sine.inOut'
        });
      }
    }
  };

  return new Phaser.Game(config);
}
