#include "urma_0195_import_jfr_default_import_jfr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0195ImportJfrDefaultImportJfrFailure> g_urma("urma_0195");

bool Urma0195ImportJfrDefaultImportJfrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to import jfr, no valid route to rjfr"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0195ImportJfrDefaultImportJfrFailure::GetName() const
{
    return "import_jfr_default 导入JFR失败";
}

std::string Urma0195ImportJfrDefaultImportJfrFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0195ImportJfrDefaultImportJfrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0195ImportJfrDefaultImportJfrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0195ImportJfrDefaultImportJfrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to import jfr, no valid route to rjfr";
}

std::string Urma0195ImportJfrDefaultImportJfrFailure::GetId() const
{
    return "urma_0195";
}
} // namespace diag
