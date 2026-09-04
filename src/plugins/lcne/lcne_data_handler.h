/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
 * witty-ub is licensed under the Mulan PSL v2.
 * You can use this software according to the terms and conditions of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *     http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
 * PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

#ifndef LCNE_DATA_HANDLER_H
#define LCNE_DATA_HANDLER_H
#include <tinyxml2.h>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include "lcne_error.h"
#include "node_data_def.h"

namespace lcne::handler {
// lcne key is  (slot, ubpu, iou)
using LcneKey = std::tuple<uint32_t, uint32_t, uint32_t>;

struct XmlPhysicalPort {
    uint32_t physicalPortId;
    std::string physicalPortStatus;
    std::optional<uint32_t> remoteSlot;
    std::optional<uint32_t> remoteUbpu;
    std::optional<uint32_t> remoteIou;
    std::optional<uint32_t> remotePhysicalPortId;

    XmlPhysicalPort() = default;

    XmlPhysicalPort(uint32_t physicalPortId, const std::string &physicalPortStatus, std::optional<uint32_t> remoteSlot,
                    std::optional<uint32_t> remoteUbpu, std::optional<uint32_t> remoteIou,
                    std::optional<uint32_t> remotePhysicalPortId)
        : physicalPortId(physicalPortId),
          physicalPortStatus(physicalPortStatus),
          remoteSlot(remoteSlot),
          remoteUbpu(remoteUbpu),
          remoteIou(remoteIou),
          remotePhysicalPortId(remotePhysicalPortId)
    {
    }
};

struct XmlNode {
    uint32_t slot;
    uint32_t ubpu;
    uint32_t iou;
    std::string ubpuType;
    std::unordered_map<uint32_t, XmlPhysicalPort> physicalPorts;

    XmlNode() = default;
    XmlNode(uint32_t slot, uint32_t ubpu, uint32_t iou, std::string &ubpuType,
            std::unordered_map<uint32_t, XmlPhysicalPort> physicalPorts)
        : slot(slot),
          ubpu(ubpu),
          iou(iou),
          ubpuType(ubpuType),
          physicalPorts(std::move(physicalPorts))
    {
    }
};

struct XmlIouInfo {
    std::string guid;
    std::string busControllerEid;
    uint32_t slotId;
    uint32_t ubpuId;
    uint32_t iouId;
    std::string primaryCna;
    std::string iouStatus;

    XmlIouInfo() = default;
    XmlIouInfo(const std::string &guid, const std::string &busControllerEid, uint32_t slotId, uint32_t ubpuId,
               uint32_t iouId, const std::string &primaryCna, const std::string &iouStatus)
        : guid(guid),
          busControllerEid(busControllerEid),
          slotId(slotId),
          ubpuId(ubpuId),
          iouId(iouId),
          primaryCna(primaryCna),
          iouStatus(iouStatus)
    {
    }
};

struct XmlAddressPhysicalPort {
    uint32_t physicalPortId;
    std::string portCna;
    std::string busPortCna;

    XmlAddressPhysicalPort() = default;
    XmlAddressPhysicalPort(uint32_t physicalPortId, const std::string &portCna, const std::string &busPortCna)
        : physicalPortId(physicalPortId),
          portCna(portCna),
          busPortCna(busPortCna)
    {
    }
};

struct XmlAddress {
    uint32_t slotId;
    uint32_t ubpuId;
    uint32_t iouId;
    std::string primaryCna;
    std::unordered_map<uint32_t, XmlAddressPhysicalPort> physicalPorts;

    XmlAddress() = default;
    XmlAddress(uint32_t slotId, uint32_t ubpuId, uint32_t iouId, const std::string &primaryCna,
               std::unordered_map<uint32_t, XmlAddressPhysicalPort> physicalPorts)
        : slotId(slotId),
          ubpuId(ubpuId),
          iouId(iouId),
          primaryCna(primaryCna),
          physicalPorts(std::move(physicalPorts))
    {
    }
};

struct XmlLogicEntity {
    std::string state;
    XmlLogicEntity() = default;
    explicit XmlLogicEntity(const std::string &state) : state(state) {}
};

LcneResult getXMLNodes(std::string requestPath, std::map<LcneKey, XmlNode> &xml_nodes);
LcneResult getNodePhysicalPorts(tinyxml2::XMLElement *element,
                                std::unordered_map<uint32_t, XmlPhysicalPort> &xml_physical_ports);
LcneResult getXMLIouInfo(std::string requestPath, std::map<LcneKey, XmlIouInfo> &xml_iou_infos);
LcneResult getXMLAddress(std::string requestPath, std::map<LcneKey, XmlAddress> &xml_addresses);
LcneResult getAddressPhysicalPorts(tinyxml2::XMLElement *element,
                                   std::unordered_map<uint32_t, XmlAddressPhysicalPort> &xml_address_physical_ports);
LcneResult GetXmlLogicEntities(std::string requestPath, std::shared_ptr<XmlLogicEntity> &xmlLogicEntity);
LcneResult generateLcneNodes(const std::map<LcneKey, XmlNode> &xml_nodes,
                             std::vector<std::shared_ptr<topology::node::Node>> &nodes);
LcneResult generateLcneUBController(const std::map<LcneKey, XmlNode> &xml_nodes,
                                    const std::map<LcneKey, XmlIouInfo> &xml_iou_infos,
                                    const std::shared_ptr<XmlLogicEntity> &xmlLogicEntity,
                                    std::vector<std::shared_ptr<topology::node::UbController>> &ub_controllers);
LcneResult generateLcnePort(const std::map<LcneKey, XmlNode> &xml_nodes,
                            const std::map<LcneKey, XmlAddress> &xml_addresses,
                            std::vector<std::shared_ptr<topology::node::Port>> &ports);
} // namespace lcne::handler
#endif // LCNE_DATA_HANDLER_H
