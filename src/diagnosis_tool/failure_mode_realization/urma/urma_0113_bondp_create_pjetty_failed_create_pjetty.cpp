#include "urma_0113_bondp_create_pjetty_failed_create_pjetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0113BondpCreatePjettyFailedCreatePjetty> g_urma("urma_0113");

bool Urma0113BondpCreatePjettyFailedCreatePjetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create pjetty %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0113BondpCreatePjettyFailedCreatePjetty::GetName() const
{
    return "bondp_create_pjetty Failed to create pjetty %.";
}

std::string Urma0113BondpCreatePjettyFailedCreatePjetty::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0113BondpCreatePjettyFailedCreatePjetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0113BondpCreatePjettyFailedCreatePjetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0113BondpCreatePjettyFailedCreatePjetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create pjetty %.";
}

std::string Urma0113BondpCreatePjettyFailedCreatePjetty::GetId() const
{
    return "urma_0113";
}
} // namespace diag
