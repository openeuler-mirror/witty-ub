#include "urma_0097_bondp_create_jfc_failed_create_bondp_comp_dev_nam.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0097BondpCreateJfcFailedCreateBondpCompDevNam> g_urma("urma_0097");

bool Urma0097BondpCreateJfcFailedCreateBondpCompDevNam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create bondp comp, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0097BondpCreateJfcFailedCreateBondpCompDevNam::GetName() const
{
    return "bondp_create_jfc Failed to create bondp comp, dev_nam";
}

std::string Urma0097BondpCreateJfcFailedCreateBondpCompDevNam::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "NULL";
}

RootCause Urma0097BondpCreateJfcFailedCreateBondpCompDevNam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0097BondpCreateJfcFailedCreateBondpCompDevNam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0097BondpCreateJfcFailedCreateBondpCompDevNam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create bondp comp, dev_name: %, eid_idx: %.";
}

std::string Urma0097BondpCreateJfcFailedCreateBondpCompDevNam::GetId() const
{
    return "urma_0097";
}
} // namespace diag
