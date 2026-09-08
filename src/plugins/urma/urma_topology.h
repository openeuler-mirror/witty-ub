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

#ifndef URMA_TOPOLOGY_H
#define URMA_TOPOLOGY_H

#include <memory>
#include <string>
#include "ubse_context.h"
#include "urma_data_def.h"
#include "urma_error.h"
#include "witty_json_module.h"
namespace urma::topo {
constexpr const char *URMA_JSON_PATH = "/var/witty-ub/urma-topology.json";
constexpr mode_t URMA_JSON_PATH_PERM_640 = 0640;
struct SessionKey {
    std::string localEid;
    std::string localJettyId;
    std::string remoteEid;
    std::string remoteJettyId;

    // 定义排序规则，使map能够存储
    bool operator<(const SessionKey &other) const
    {
        if (localEid != other.localEid) {
            return localEid < other.localEid;
        }
        if (localJettyId != other.localJettyId) {
            return localJettyId < other.localJettyId;
        }
        if (remoteEid != other.remoteEid) {
            return remoteEid < other.remoteEid;
        }
        return remoteJettyId < other.remoteJettyId;
    }

    std::string ToString() const
    {
        return "local eid=" + localEid + ", local jetty_id=" + localJettyId + ", remote eid=" + remoteEid +
               ", remote jetty_id=" + remoteJettyId;
    }
};

class URMATopology {
public:
    URMATopology()
    {
        jsonModule = ubse::context::UbseContext::GetInstance().GetModule<witty_json::module::JSONModule>();
    };
    URMAResult ParseUMQLog(std::string filePath, std::map<SessionKey, std::string> &activeSessions);
    URMAResult CreateTopology(ubse::context::TopoToolsArgs &args);

private:
    std::shared_ptr<witty_json::module::JSONModule> jsonModule;
    std::vector<std::string> CollectLogFiles(const std::string &filePath);
    URMAResult ProcessLogFile(const std::string &logFile, std::map<SessionKey, std::string> &activeSessions);
    URMAResult CreatePodModeTopology(const ubse::context::TopoToolsArgs &args, std::vector<topology::urma::Pod> &pods,
                                     std::vector<topology::urma::Jetty> &jetties,
                                     std::vector<topology::urma::URMADevice> &urma_devices);
    URMAResult CreateNormalModeTopology(const std::map<std::string, std::string> &input_umq_log_path,
                                        std::vector<topology::urma::Jetty> &jetties,
                                        std::vector<topology::urma::URMADevice> &urma_devices);
};
} // namespace urma::topo
#endif
