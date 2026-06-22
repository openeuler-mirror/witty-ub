#include "urma_failure_165.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure165> g_urma("urma_165");

bool UrmaFailure165::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_slide_wnd_add") != std::string::npos &&
           message.find("Invalid param wnd") != std::string::npos;
}

std::string UrmaFailure165::GetName() const
{
    return "BDP、slide、WND状态不满足要求导致添加BDP、slide、WND失败";
}

std::string UrmaFailure165::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_add执行添加BDP、slide、WND时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure165::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure165::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure165::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_add，Invalid param wnd。";
}

std::string UrmaFailure165::GetId() const
{
    return "urma_165";
}
} // namespace diag
