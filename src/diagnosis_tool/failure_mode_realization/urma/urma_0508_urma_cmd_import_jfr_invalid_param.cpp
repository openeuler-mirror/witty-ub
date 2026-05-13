#include "urma_0508_urma_cmd_import_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0508UrmaCmdImportJfrInvalidParam> g_urma("urma_0508");

bool Urma0508UrmaCmdImportJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0508UrmaCmdImportJfrInvalidParam::GetName() const
{
    return "urma_cmd_import_jfr 参数非法";
}

std::string Urma0508UrmaCmdImportJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || tjfr == NULL || cfg == NULL || cfg->token "
           "== NULL`；该路径返回 -1";
}

RootCause Urma0508UrmaCmdImportJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0508UrmaCmdImportJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0508UrmaCmdImportJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0508UrmaCmdImportJfrInvalidParam::GetId() const
{
    return "urma_0508";
}
} // namespace diag
