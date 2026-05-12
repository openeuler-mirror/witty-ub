#include "urma_1226_urma_read_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1226UrmaReadInvalidParam> g_urma("urma_1226");

bool Urma1226UrmaReadInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1226UrmaReadInvalidParam::GetName() const
{
    return "urma_read 参数非法";
}

std::string Urma1226UrmaReadInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->post_jfs_wr == NULL || target_jfr == NULL || "
           "dst_tseg == NULL || src_tseg `；该路径返回 URMA_EINVAL";
}

RootCause Urma1226UrmaReadInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1226UrmaReadInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1226UrmaReadInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1226UrmaReadInvalidParam::GetId() const
{
    return "urma_1226";
}
} // namespace diag
