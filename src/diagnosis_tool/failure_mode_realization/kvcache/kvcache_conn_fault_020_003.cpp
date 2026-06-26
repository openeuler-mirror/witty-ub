#include "kvcache_conn_fault_020_003.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault020_003> g_kvcacheconnfault("kvcache_conn_fault_020_003");

bool KvcacheConnFault020_003::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return (message.find("[UDS_CONNECT_FAILED]") != std::string::npos ||
            message.find("[SHM_FD_TRANSFER_FAILED]") != std::string::npos);
}

std::string KvcacheConnFault020_003::GetName() const
{
    return "1001/1002 → OS侧UDS连接失败/SHM fd传输失败。";
}

std::string KvcacheConnFault020_003::GetRootCauseDesc() const
{
    return "同机UDS路径不存在/权限不足/fd耗尽，SCM_RIGHTS发送失败多为fd耗尽或权限，"
           "属于OS层（08手册:L210, L335）。";
}

RootCause KvcacheConnFault020_003::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault020_003::GetFixSuggDesc() const
{
    return "检查UDS路径和权限；检查fd上限（ls /proc/<pid>/fd | wc -l "
           "vs ulimit -n）（08手册:L335）。";
}

std::string KvcacheConnFault020_003::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L210, L335）：匹配[UDS_CONNECT_FAILED]或[SHM_FD_TRANSFER_FAILED]。";
}

std::string KvcacheConnFault020_003::GetId() const
{
    return "kvcache_conn_fault_020_003";
}
} // namespace diag
