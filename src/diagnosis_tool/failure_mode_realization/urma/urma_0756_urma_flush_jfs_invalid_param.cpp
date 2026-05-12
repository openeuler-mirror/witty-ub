#include "urma_0756_urma_flush_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0756UrmaFlushJfsInvalidParam> g_urma("urma_0756");

bool Urma0756UrmaFlushJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0756UrmaFlushJfsInvalidParam::GetName() const
{
    return "urma_flush_jfs 参数非法";
}

std::string Urma0756UrmaFlushJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || cr == NULL || cr_cnt <= 0 || (uint32_t)cr_cnt > "
           "jfs->jfs_cfg.depth`；该路径返回 (int)(-URMA_EINVAL)";
}

RootCause Urma0756UrmaFlushJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0756UrmaFlushJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0756UrmaFlushJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0756UrmaFlushJfsInvalidParam::GetId() const
{
    return "urma_0756";
}
} // namespace diag
