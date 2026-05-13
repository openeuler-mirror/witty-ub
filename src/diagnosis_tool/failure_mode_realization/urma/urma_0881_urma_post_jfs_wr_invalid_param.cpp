#include "urma_0881_urma_post_jfs_wr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0881UrmaPostJfsWrInvalidParam> g_urma("urma_0881");

bool Urma0881UrmaPostJfsWrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0881UrmaPostJfsWrInvalidParam::GetName() const
{
    return "urma_post_jfs_wr 参数非法";
}

std::string Urma0881UrmaPostJfsWrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->post_jfs_wr == NULL || wr == NULL || bad_wr == "
           "NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0881UrmaPostJfsWrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0881UrmaPostJfsWrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0881UrmaPostJfsWrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0881UrmaPostJfsWrInvalidParam::GetId() const
{
    return "urma_0881";
}
} // namespace diag
