'use strict';

function safeReadUtf8(ptr, fallbackLength) {
  if (ptr.isNull()) {
    return null;
  }
  try {
    return ptr.readUtf8String();
  } catch (_) {
    try {
      return ptr.readUtf8String(fallbackLength);
    } catch (_) {
      return null;
    }
  }
}

function readPayload(ptr, length) {
  if (ptr.isNull() || length <= 0) {
    return "";
  }
  const bytes = ptr.readByteArray(length);
  if (bytes === null) {
    return "";
  }
  const buffer = new Uint8Array(bytes);
  let ascii = true;
  for (let i = 0; i < buffer.length; i++) {
    const b = buffer[i];
    if ((b < 0x20 || b > 0x7e) && b !== 0x09 && b !== 0x0a && b !== 0x0d) {
      ascii = false;
      break;
    }
  }
  if (ascii) {
    return String.fromCharCode.apply(null, buffer);
  }
  return Array.from(buffer).map((b) => b.toString(16).padStart(2, '0')).join('');
}

function logPublish(kind, topic, payload, extra) {
  send({
    type: 'mqtt-publish',
    kind,
    topic,
    payload,
    extra
  });
}

function hookPublish() {
  let mqttModule = null;
  try {
    mqttModule = Process.getModuleByName('paho-mqtt3cs.dll');
  } catch (error) {
    send({
      type: 'hook-error',
      hook: 'Process.getModuleByName',
      error: String(error)
    });
    return;
  }

  const exports = [
    ['MQTTClient_publish', function (args) {
      const topic = safeReadUtf8(args[1], 512);
      const length = args[2].toInt32();
      const payload = readPayload(args[3], length);
      const qos = args[4].toInt32();
      const retained = args[5].toInt32();
      logPublish('MQTTClient_publish', topic, payload, { length, qos, retained });
    }],
    ['MQTTClient_publishMessage', function (args) {
      const topic = safeReadUtf8(args[1], 512);
      const msg = args[2];
      const length = msg.add(8).readS32();
      const payloadPtr = msg.add(16).readPointer();
      const qos = msg.add(24).readS32();
      const retained = msg.add(28).readS32();
      const dup = msg.add(32).readS32();
      const msgid = msg.add(36).readS32();
      const payload = readPayload(payloadPtr, length);
      logPublish('MQTTClient_publishMessage', topic, payload, { length, qos, retained, dup, msgid });
    }],
    ['MQTTClient_publish5', function (args) {
      const topic = safeReadUtf8(args[1], 512);
      const length = args[2].toInt32();
      const payload = readPayload(args[3], length);
      const qos = args[4].toInt32();
      const retained = args[5].toInt32();
      logPublish('MQTTClient_publish5', topic, payload, { length, qos, retained });
    }],
    ['MQTTClient_publishMessage5', function (args) {
      const topic = safeReadUtf8(args[1], 512);
      const msg = args[2];
      const length = msg.add(8).readS32();
      const payloadPtr = msg.add(16).readPointer();
      const qos = msg.add(24).readS32();
      const retained = msg.add(28).readS32();
      const dup = msg.add(32).readS32();
      const msgid = msg.add(36).readS32();
      const payload = readPayload(payloadPtr, length);
      logPublish('MQTTClient_publishMessage5', topic, payload, { length, qos, retained, dup, msgid });
    }]
  ];

  let attached = 0;
  for (const [name, handler] of exports) {
    let address = null;
    try {
      address = mqttModule.getExportByName(name);
    } catch (_) {
      address = null;
    }
    if (address === null) {
      continue;
    }
    Interceptor.attach(address, {
      onEnter(args) {
        try {
          handler(args);
        } catch (error) {
          send({
            type: 'hook-error',
            hook: name,
            error: String(error)
          });
        }
      }
    });
    attached++;
  }

  send({
    type: 'hook-ready',
    module: 'paho-mqtt3cs.dll',
    attached
  });
}

setImmediate(hookPublish);
