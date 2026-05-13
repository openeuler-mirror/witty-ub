#include "urma_0839_urma_set_jfs_opt_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0839UrmaSetJfsOptInvalidParam> g_urma("urma_0839");

bool Urma0839UrmaSetJfsOptInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0839UrmaSetJfsOptInvalidParam::GetName() const
{
    return "urma_set_jfs_opt 参数非法";
}

std::string Urma0839UrmaSetJfsOptInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma0839UrmaSetJfsOptInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0839UrmaSetJfsOptInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0839UrmaSetJfsOptInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0839UrmaSetJfsOptInvalidParam::GetId() const
{
    return "urma_0839";
}
} // namespace diag
