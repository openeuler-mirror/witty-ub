#include "kvcache_conn_fault_008.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault008> g_kvcacheconnfault("kvcache_conn_fault_008");

bool KvcacheConnFault008::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    int statusCode = std::stoi(fields[7]);
    return (statusCode == 7);
}

std::string KvcacheConnFault008::GetName() const
{
    return "错误码7 K_IO_ERROR (OS)。";
}

std::string KvcacheConnFault008::GetRootCauseDesc() const
{
    return "IO错误，可能原因包括块设备/文件系统故障或分布式网盘POSIX接口失败（08手册:L331）。";
}

RootCause KvcacheConnFault008::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault008::GetFixSuggDesc() const
{
    return "dmesg查看IO错误日志；查块设备/文件系统健康状态；分布式网盘POSIX接口失败同样归此类别（08手册:L331）。";
}

std::string KvcacheConnFault008::GetValidationMethodDesc() const
{
    return "通过access log识别（08手册:L132, L196）：access log中status_code（第8列）为7。";
}

std::string KvcacheConnFault008::GetId() const
{
    return "kvcache_conn_fault_008";
}
} // namespace diag
