#include "urma_failure_465.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure465> g_urma("urma_465");

bool UrmaFailure465::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_jfc_opt") != std::string::npos &&
           message.find("Failed to exec ops->get_jfc_opt.") != std::string::npos;
}

std::string UrmaFailure465::GetName() const
{
    return "下层查询返回失败导致获取JFC失败";
}

std::string UrmaFailure465::GetRootCauseDesc() const
{
    return "urma_get_jfc_opt需要从provider、驱动或缓存中获取JFC状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure465::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure465::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure465::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfc_opt，Failed to exec ops->get_jfc_opt.。";
}

std::string UrmaFailure465::GetId() const
{
    return "urma_465";
}
} // namespace diag
