#include "urma_failure_033.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure033> g_urma("urma_033");

bool UrmaFailure033::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_slide_wnd_init") != std::string::npos &&
           message.find("Invalid param: total_size <= window_size") != std::string::npos;
}

std::string UrmaFailure033::GetName() const
{
    return "BDP、slide、WND状态不满足要求导致初始化BDP、slide、WND失败";
}

std::string UrmaFailure033::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_init执行初始化BDP、slide、WND时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure033::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure033::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure033::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_init，Invalid param: total_size <= window_size。";
}

std::string UrmaFailure033::GetId() const
{
    return "urma_033";
}
} // namespace diag
