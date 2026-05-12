#include "urma_1141_urma_cmd_unimport_seg_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1141UrmaCmdUnimportSegInvalidParam> g_urma("urma_1141");

bool Urma1141UrmaCmdUnimportSegInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1141UrmaCmdUnimportSegInvalidParam::GetName() const
{
    return "urma_cmd_unimport_seg 参数非法";
}

std::string Urma1141UrmaCmdUnimportSegInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `tseg == NULL || tseg->urma_ctx == NULL || tseg->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma1141UrmaCmdUnimportSegInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1141UrmaCmdUnimportSegInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1141UrmaCmdUnimportSegInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1141UrmaCmdUnimportSegInvalidParam::GetId() const
{
    return "urma_1141";
}
} // namespace diag
