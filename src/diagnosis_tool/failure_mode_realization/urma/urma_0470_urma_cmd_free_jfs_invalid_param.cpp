#include "urma_0470_urma_cmd_free_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0470UrmaCmdFreeJfsInvalidParam> g_urma("urma_0470");

bool Urma0470UrmaCmdFreeJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0470UrmaCmdFreeJfsInvalidParam::GetName() const
{
    return "urma_cmd_free_jfs 参数非法";
}

std::string Urma0470UrmaCmdFreeJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || jfs->urma_ctx == NULL || jfs->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma0470UrmaCmdFreeJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0470UrmaCmdFreeJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0470UrmaCmdFreeJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0470UrmaCmdFreeJfsInvalidParam::GetId() const
{
    return "urma_0470";
}
} // namespace diag
