#include "urma_failure_250.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure250> g_urma("urma_250");

bool UrmaFailure250::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_jfr_opt") != std::string::npos &&
           message.find("Failed to exec ops->get_jfr_opt.") != std::string::npos;
}

std::string UrmaFailure250::GetName() const
{
    return "下层查询返回失败导致获取JFR失败";
}

std::string UrmaFailure250::GetRootCauseDesc() const
{
    return "urma_get_jfr_opt需要从provider、驱动或缓存中获取JFR状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure250::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure250::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure250::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfr_opt，Failed to exec ops->get_jfr_opt.。";
}

std::string UrmaFailure250::GetId() const
{
    return "urma_250";
}
} // namespace diag
