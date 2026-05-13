#include "urma_0531_urma_cmd_query_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0531UrmaCmdQueryJfsInvalidParam> g_urma("urma_0531");

bool Urma0531UrmaCmdQueryJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0531UrmaCmdQueryJfsInvalidParam::GetName() const
{
    return "urma_cmd_query_jfs 参数非法";
}

std::string Urma0531UrmaCmdQueryJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || jfs->urma_ctx == NULL || jfs->urma_ctx->dev_fd < 0 || cfg == "
           "NULL || attr == NULL`；该路径返回 -1";
}

RootCause Urma0531UrmaCmdQueryJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0531UrmaCmdQueryJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0531UrmaCmdQueryJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0531UrmaCmdQueryJfsInvalidParam::GetId() const
{
    return "urma_0531";
}
} // namespace diag
