#include "urma_0463_urma_cmd_free_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0463UrmaCmdFreeJfcInvalidParam> g_urma("urma_0463");

bool Urma0463UrmaCmdFreeJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0463UrmaCmdFreeJfcInvalidParam::GetName() const
{
    return "urma_cmd_free_jfc 参数非法";
}

std::string Urma0463UrmaCmdFreeJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || jfc->urma_ctx == NULL || jfc->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma0463UrmaCmdFreeJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0463UrmaCmdFreeJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0463UrmaCmdFreeJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0463UrmaCmdFreeJfcInvalidParam::GetId() const
{
    return "urma_0463";
}
} // namespace diag
