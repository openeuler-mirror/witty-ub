#include "urma_0210_bondp_create_comp_failed_create_comp_type.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0210BondpCreateCompFailedCreateCompType> g_urma("urma_0210");

bool Urma0210BondpCreateCompFailedCreateCompType::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to create comp %, type: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0210BondpCreateCompFailedCreateCompType::GetName() const
{
    return "bondp_create_comp Failed to create comp %, type: %.";
}

std::string Urma0210BondpCreateCompFailedCreateCompType::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0210BondpCreateCompFailedCreateCompType::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0210BondpCreateCompFailedCreateCompType::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0210BondpCreateCompFailedCreateCompType::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to create comp %, type: %.";
}

std::string Urma0210BondpCreateCompFailedCreateCompType::GetId() const
{
    return "urma_0210";
}
} // namespace diag
