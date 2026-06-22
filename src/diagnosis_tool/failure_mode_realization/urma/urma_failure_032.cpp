#include "urma_failure_032.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure032> g_urma("urma_032");

bool UrmaFailure032::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_slide_wnd_init") != std::string::npos &&
           message.find("Invalid param wnd") != std::string::npos;
}

std::string UrmaFailure032::GetName() const
{
    return "BDP、slide、WND状态不满足要求导致初始化BDP、slide、WND失败";
}

std::string UrmaFailure032::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_init执行初始化BDP、slide、WND时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure032::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure032::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure032::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_init，Invalid param wnd。";
}

std::string UrmaFailure032::GetId() const
{
    return "urma_032";
}
} // namespace diag
