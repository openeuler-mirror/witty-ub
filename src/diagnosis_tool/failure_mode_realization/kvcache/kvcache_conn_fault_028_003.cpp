#include "kvcache_conn_fault_028_003.h"

#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<KvcacheConnFault028_003> g_kvcacheconnfault("kvcache_conn_fault_028_003");

bool KvcacheConnFault028_003::IsValid(const std::vector<std::string> &fields)
{
    if (fields.size() <= 7) {
        return false;
    }
    const std::string &message = fields[7];
    return message.find("[URMA_RECREATE_JFS]") != std::string::npos;
}

std::string KvcacheConnFault028_003::GetName() const
{
    return "URMA_RECREATE_JFS + cqeStatus=9（JFS异常自动重建）。";
}

std::string KvcacheConnFault028_003::GetRootCauseDesc() const
{
    return "JFS ACK超时触发的自动重建，通常自愈；若失败则需进一步排查UMDK/"
           "驱动（08手册:L299）。";
}

RootCause KvcacheConnFault028_003::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string KvcacheConnFault028_003::GetFixSuggDesc() const
{
    return "若无URMA_RECREATE_JFS_FAILED则视为自愈成功无需处理；若有FAILED则见kvcache_conn_fault_028_004（08手册:L299）。";
}

std::string KvcacheConnFault028_003::GetValidationMethodDesc() const
{
    return "通过日志关键字识别（08手册:L299）：匹配[URMA_RECREATE_JFS]且cqeStatus=9。";
}

std::string KvcacheConnFault028_003::GetId() const
{
    return "kvcache_conn_fault_028_003";
}
} // namespace diag
