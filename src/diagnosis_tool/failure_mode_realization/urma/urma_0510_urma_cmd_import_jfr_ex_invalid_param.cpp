#include "urma_0510_urma_cmd_import_jfr_ex_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0510UrmaCmdImportJfrExInvalidParam> g_urma("urma_0510");

bool Urma0510UrmaCmdImportJfrExInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0510UrmaCmdImportJfrExInvalidParam::GetName() const
{
    return "urma_cmd_import_jfr_ex 参数非法";
}

std::string Urma0510UrmaCmdImportJfrExInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || tjfr == NULL || cfg == NULL || cfg->token "
           "== NULL || ex_cfg == NUL`；该路径返回 -1";
}

RootCause Urma0510UrmaCmdImportJfrExInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0510UrmaCmdImportJfrExInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0510UrmaCmdImportJfrExInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0510UrmaCmdImportJfrExInvalidParam::GetId() const
{
    return "urma_0510";
}
} // namespace diag
