#include "urma_1155_urma_unimport_seg_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1155UrmaUnimportSegInvalidParam> g_urma("urma_1155");

bool Urma1155UrmaUnimportSegInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1155UrmaUnimportSegInvalidParam::GetName() const
{
    return "urma_unimport_seg 参数非法";
}

std::string Urma1155UrmaUnimportSegInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `tseg == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1155UrmaUnimportSegInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1155UrmaUnimportSegInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1155UrmaUnimportSegInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1155UrmaUnimportSegInvalidParam::GetId() const
{
    return "urma_1155";
}
} // namespace diag
