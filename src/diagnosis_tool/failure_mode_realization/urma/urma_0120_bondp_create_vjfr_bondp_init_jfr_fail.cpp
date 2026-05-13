#include "urma_0120_bondp_create_vjfr_bondp_init_jfr_fail.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0120BondpCreateVjfrBondpInitJfrFail> g_urma("urma_0120");

bool Urma0120BondpCreateVjfrBondpInitJfrFail::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bondp init jfr fail: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0120BondpCreateVjfrBondpInitJfrFail::GetName() const
{
    return "bondp_create_vjfr bondp init jfr fail: %.";
}

std::string Urma0120BondpCreateVjfrBondpInitJfrFail::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `ret`；该路径返回 -1";
}

RootCause Urma0120BondpCreateVjfrBondpInitJfrFail::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0120BondpCreateVjfrBondpInitJfrFail::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0120BondpCreateVjfrBondpInitJfrFail::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bondp init jfr fail: %.";
}

std::string Urma0120BondpCreateVjfrBondpInitJfrFail::GetId() const
{
    return "urma_0120";
}
} // namespace diag
