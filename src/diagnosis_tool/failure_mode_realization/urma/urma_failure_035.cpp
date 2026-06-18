#include "urma_failure_035.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure035> g_urma("urma_035");

bool UrmaFailure035::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_slide_wnd_uninit") != std::string::npos &&
           message.find("Invalid param wnd") != std::string::npos;
}

std::string UrmaFailure035::GetName() const
{
    return "BDP、slide、WND状态不满足要求导致bdpBDP、slide、WND失败";
}

std::string UrmaFailure035::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_uninit执行bdpBDP、slide、WND时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure035::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure035::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure035::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_uninit，Invalid param wnd。";
}

std::string UrmaFailure035::GetId() const
{
    return "urma_035";
}
} // namespace diag
