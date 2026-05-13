#include "urma_0879_urma_post_jfr_wr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0879UrmaPostJfrWrInvalidParam> g_urma("urma_0879");

bool Urma0879UrmaPostJfrWrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0879UrmaPostJfrWrInvalidParam::GetName() const
{
    return "urma_post_jfr_wr 参数非法";
}

std::string Urma0879UrmaPostJfrWrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->post_jfr_wr == NULL || wr == NULL || bad_wr == "
           "NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0879UrmaPostJfrWrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0879UrmaPostJfrWrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0879UrmaPostJfrWrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0879UrmaPostJfrWrInvalidParam::GetId() const
{
    return "urma_0879";
}
} // namespace diag
