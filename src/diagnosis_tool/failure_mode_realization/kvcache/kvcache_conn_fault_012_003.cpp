#include "kvcache_conn_fault_012_003.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault012_003> g_kvcacheconnfault("kvcache_conn_fault_012_003");

bool KvcacheConnFault012_003::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("etcd is timeout") != std::string::npos ||
            message.find("etcd is unavailable") != std::string::npos);
}

std::string KvcacheConnFault012_003::GetName() const
{
    return "三方etcd（Master/Worker日志中出现etcd超时）。";
}

std::string KvcacheConnFault012_003::GetRootCauseDesc() const
{
    return "主责写三方etcd（08手册:L273）。";
}

RootCause KvcacheConnFault012_003::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault012_003::GetFixSuggDesc() const
{
    return "systemctl status etcd；etcdctl endpoint status；排查到etcd的网络（08手册:L273）。";
}

std::string KvcacheConnFault012_003::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L273）：匹配etcd is timeout或etcd "
           "is unavailable；配合resource.log中ETCD_QUEUE堆积。";
}

std::string KvcacheConnFault012_003::GetId() const
{
    return "kvcache_conn_fault_012_003";
}
} // namespace diag
