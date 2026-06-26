#include "kvcache_conn_fault_011.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault011> g_kvcacheconnfault("kvcache_conn_fault_011");

bool KvcacheConnFault011::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 25);
}

std::string KvcacheConnFault011::GetName() const
{
    return "错误码25 K_MASTER_TIMEOUT (三方etcd)。";
}

std::string KvcacheConnFault011::GetRootCauseDesc() const
{
    return "etcd集群或到etcd的网络问题，属于三方etcd责任（08手册:L135）。";
}

RootCause KvcacheConnFault011::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault011::GetFixSuggDesc() const
{
    return "systemctl status etcd；etcdctl endpoint status；排查到etcd的网络（08手册:L273）。";
}

std::string KvcacheConnFault011::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L135, L196）：access log中status_code（第8列）为25；"
           "配合Worker日志中etcd is timeout/unavailable和resource.log中ETCD_QUEUE堆积。";
}

std::string KvcacheConnFault011::GetId() const
{
    return "kvcache_conn_fault_011";
}
} // namespace diag
