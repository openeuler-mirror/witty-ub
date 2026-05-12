#include "urma_1035_urma_check_seg_cfg_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1035UrmaCheckSegCfgFailure> g_urma("urma_1035");

bool Urma1035UrmaCheckSegCfgFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "token_id must set when token_id_valid is true, or must NULL when token_id_valid is false."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1035UrmaCheckSegCfgFailure::GetName() const
{
    return "urma_check_seg_cfg 设置属性失败";
}

std::string Urma1035UrmaCheckSegCfgFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "false";
}

RootCause Urma1035UrmaCheckSegCfgFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1035UrmaCheckSegCfgFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1035UrmaCheckSegCfgFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：token_id must set when token_id_valid is true, or must NULL when "
           "token_id_valid is false.";
}

std::string Urma1035UrmaCheckSegCfgFailure::GetId() const
{
    return "urma_1035";
}
} // namespace diag
