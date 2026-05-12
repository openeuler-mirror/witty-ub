#include "urma_0447_urma_cmd_delete_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0447UrmaCmdDeleteJfsInvalidParam> g_urma("urma_0447");

bool Urma0447UrmaCmdDeleteJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0447UrmaCmdDeleteJfsInvalidParam::GetName() const
{
    return "urma_cmd_delete_jfs 参数非法";
}

std::string Urma0447UrmaCmdDeleteJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || jfs->urma_ctx == NULL || jfs->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma0447UrmaCmdDeleteJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0447UrmaCmdDeleteJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0447UrmaCmdDeleteJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0447UrmaCmdDeleteJfsInvalidParam::GetId() const
{
    return "urma_0447";
}
} // namespace diag
