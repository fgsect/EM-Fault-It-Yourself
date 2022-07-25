/* EMFI Station - Orchestrate electromagnetic fault injection attacks     */
/* Copyright (C) 2022 Niclas Kühnapfel                                    */
/*                                                                        */
/* This program is free software: you can redistribute it and/or modify   */
/* it under the terms of the GNU General Public License as published by   */
/* the Free Software Foundation, either version 3 of the License, or      */
/* (at your option) any later version.                                    */
/*                                                                        */
/* This program is distributed in the hope that it will be useful,        */
/* but WITHOUT ANY WARRANTY; without even the implied warranty of         */
/* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          */
/* GNU General Public License for more details.                           */
/*                                                                        */
/* You should have received a copy of the GNU General Public License      */
/* along with this program.  If not, see <https://www.gnu.org/licenses/>. */

const port = String(Number(window.location.port) + 1)
const socket = new WebSocket("ws://" + window.location.hostname + ":" + port);

const app = Vue.createApp({
    data() {
        return {
            errorMsg: '',
            state: {
                mode: '',
                position: '',
                temperature: '',
                attacks: [],
                progress: '',
                safe_z: 100,
            },
            settings: {
                moveSpeed: 100,
                moveStep: 1,
                homeX: true,
                homeY: true,
                homeZ: true,
                absMoveSpeed: 100,
                absMoveX: 0,
                absMoveY: 0,
                absMoveZ: 0,
                joySpeed: 100,
                joyStep: 2,
                selectedAttack: '',
                safeZ: 100,
            },
            stream: '',
            cam: 'thermal'
        }
    },
    methods: {
        move(axis, direction, speed, step) {
            console.log('move: ' + axis + direction + speed + step);
            let x = 0, y = 0, z = 0;
            switch (axis) {
                case 'x':
                    x = step * direction;
                    break;
                case 'y':
                    y = step * direction;
                    break;
                case 'z':
                    z = step * direction;
                    break;
                default:
                    break;
            }
            this.sendCmd('step', {'speed': speed, 'x': x, 'y': y, 'z': z});
        },
        home(x, y, z) {
            console.log('home: ' + x + y + z);
            this.sendCmd('home', {'x': x, 'y': y, 'z': z});
        },
        absMove(speed, x, y, z) {
            console.log('absmove: ' + speed + x + y + z);
            this.sendCmd('move', {'speed': speed, 'x': x, 'y': y, 'z': z});
        },
        toggleAttack(name) {
            if (this.state.mode === 'Attack') {
                this.sendCmd('stopAttack', {});
            } else {
                this.sendCmd('startAttack', {'name': name});
            }
        },
        async toggleJoystick(speed, step) {
            if (this.state.mode === 'Joystick') {
                this.sendCmd('disableJoystick', {'speed': speed, 'step': step});
            } else {
                this.sendCmd('enableJoystick', {'speed': speed, 'step': step});
            }
        },
        showError(msg) {
            this.errorMsg = msg;
            this.errorModal.show();
        },
        sendCmd(cmd, args) {
            let obj = Object.assign({'type': 'command', 'cmd': cmd}, args);
            socket.send(JSON.stringify(obj));
        },
        switchCam(name) {
            this.cam = name;
        },
        setSafeZ(z) {
            this.sendCmd('safeZ', {'z': z});
        }
    },
    mounted() {
        this.errorModal = new bootstrap.Modal(document.getElementById('error-modal'), {
          keyboard: false
        });
    },
    created() {
        socket.onmessage = (msg) => {
            let data = JSON.parse(msg.data)
            if (data.type === 'microscope') {
                if (this.cam === 'microscope') {
                    this.stream = data.image;
                }
            } else if (data.type === 'thermal_camera') {
                if (this.cam === 'thermal') {
                    this.stream = data.image;
                }
            } else if (data.type === 'calibration') {
                if (this.cam === 'calibration') {
                    this.stream = data.image;
                }
            } else if (data.type === 'error') {
                this.showError(data.message);
            } else if (data.type === 'state') {
                this.state = data.state;
            } else {
                console.log('Unknown message: ' + data);
            }
        };
    }
});

const vm = app.mount('#app');