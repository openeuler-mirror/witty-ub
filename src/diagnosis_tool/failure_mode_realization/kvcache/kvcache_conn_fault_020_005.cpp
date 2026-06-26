#include "kvcache_conn_fault_020_005.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_005> g_kvcacheconnfault("kvcache_conn_fault_020_005");

bool KvcacheConnFault020_005::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("etcd is timeout") != std::string::npos ||
            message.find("etcd is unavailable") != std::string::npos);
}

std::string KvcacheConnFault020_005::GetName() const
{
    return "1001/1002 → 三方etcd（etcd超时/不可用）。";
}

std::string KvcacheConnFault020_005::GetRootCauseDesc() const
{
    return "etcd集群或到etcd的网络问题，属于三方etcd责任（08手册:L217）。";
}

RootCause KvcacheConnFault020_005::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_005::GetFixSuggDesc() const
{
    return "systemctl status etcd；etcdctl endpoint status；排查到etcd的网络（08手册:L273）。";
}

std::string KvcacheConnFault020_005::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L217）：匹配etcd is timeout或etcd "
           "is unavailable，常同屏出现1002/25错误码。";
}

std::string KvcacheConnFault020_005::GetId() const
{
    return "kvcache_conn_fault_020_005";
}
} // namespace diag
