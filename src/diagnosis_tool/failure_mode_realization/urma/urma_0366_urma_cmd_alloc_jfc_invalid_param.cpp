#include "urma_0366_urma_cmd_alloc_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0366UrmaCmdAllocJfcInvalidParam> g_urma("urma_0366");

bool Urma0366UrmaCmdAllocJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0366UrmaCmdAllocJfcInvalidParam::GetName() const
{
    return "urma_cmd_alloc_jfc 参数非法";
}

std::string Urma0366UrmaCmdAllocJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || jfc == NULL || cfg == NULL`；该路径返回 -1";
}

RootCause Urma0366UrmaCmdAllocJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0366UrmaCmdAllocJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0366UrmaCmdAllocJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0366UrmaCmdAllocJfcInvalidParam::GetId() const
{
    return "urma_0366";
}
} // namespace diag
