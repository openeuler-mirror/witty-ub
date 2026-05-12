#include "urma_0169_bondp_import_pjfr_currently_jfr_does_not_support_sing.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0169BondpImportPjfrCurrentlyJfrDoesNotSupportSing> g_urma("urma_0169");

bool Urma0169BondpImportPjfrCurrentlyJfrDoesNotSupportSing::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Currently, jfr does not support single-path mode."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0169BondpImportPjfrCurrentlyJfrDoesNotSupportSing::GetName() const
{
    return "bondp_import_pjfr Currently, jfr does not support sing";
}

std::string Urma0169BondpImportPjfrCurrentlyJfrDoesNotSupportSing::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 -1";
}

RootCause Urma0169BondpImportPjfrCurrentlyJfrDoesNotSupportSing::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0169BondpImportPjfrCurrentlyJfrDoesNotSupportSing::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0169BondpImportPjfrCurrentlyJfrDoesNotSupportSing::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Currently, jfr does not support single-path mode.";
}

std::string Urma0169BondpImportPjfrCurrentlyJfrDoesNotSupportSing::GetId() const
{
    return "urma_0169";
}
} // namespace diag
