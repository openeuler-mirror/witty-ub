#include "urma_1024_urma_cmd_import_seg_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1024UrmaCmdImportSegInvalidParam> g_urma("urma_1024");

bool Urma1024UrmaCmdImportSegInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1024UrmaCmdImportSegInvalidParam::GetName() const
{
    return "urma_cmd_import_seg 参数非法";
}

std::string Urma1024UrmaCmdImportSegInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || tseg == NULL || cfg == NULL`；该路径返回 "
           "-1";
}

RootCause Urma1024UrmaCmdImportSegInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1024UrmaCmdImportSegInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1024UrmaCmdImportSegInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1024UrmaCmdImportSegInvalidParam::GetId() const
{
    return "urma_1024";
}
} // namespace diag
