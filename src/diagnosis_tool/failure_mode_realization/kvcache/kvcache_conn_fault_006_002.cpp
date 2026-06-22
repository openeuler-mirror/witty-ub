#include "kvcache_conn_fault_006_002.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault006_002> g_kvcacheconnfault("kvcache_conn_fault_006_002");

bool KvcacheConnFault006_002::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("etcd is timeout") != std::string::npos ||
            message.find("etcd is unavailable") != std::string::npos);
}

std::string KvcacheConnFault006_002::GetName() const
{
    return "code=5 + etcd is timeout/unavailable (三方etcd)。";
}

std::string KvcacheConnFault006_002::GetRootCauseDesc() const
{
    return "etcd集群或到etcd的网络问题，属于三方etcd责任（08手册:L217）。";
}

RootCause KvcacheConnFault006_002::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault006_002::GetFixSuggDesc() const
{
    return "systemctl status etcd；etcdctl endpoint status；排查到etcd的网络（08手册:L273）。";
}

std::string KvcacheConnFault006_002::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L193, L217）：匹配etcd is timeout或etcd "
           "is unavailable。";
}

std::string KvcacheConnFault006_002::GetId() const
{
    return "kvcache_conn_fault_006_002";
}
} // namespace diag
