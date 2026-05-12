#include "urma_1121_urma_write_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1121UrmaWriteInvalidParam> g_urma("urma_1121");

bool Urma1121UrmaWriteInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1121UrmaWriteInvalidParam::GetName() const
{
    return "urma_write 参数非法";
}

std::string Urma1121UrmaWriteInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `dp_ops == NULL || dp_ops->post_jfs_wr == NULL || target_jfr == NULL || "
           "dst_tseg == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1121UrmaWriteInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1121UrmaWriteInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1121UrmaWriteInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1121UrmaWriteInvalidParam::GetId() const
{
    return "urma_1121";
}
} // namespace diag
