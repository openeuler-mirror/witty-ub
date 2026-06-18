#include "urma_failure_682.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure682> g_urma("urma_682");

bool UrmaFailure682::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_slide_wnd_seq_in_window") != std::string::npos &&
           message.find("Invalid param wnd") != std::string::npos;
}

std::string UrmaFailure682::GetName() const
{
    return "BDP、slide、WND状态不满足要求导致bdpBDP、slide、WND失败";
}

std::string UrmaFailure682::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_seq_in_"
           "window执行bdpBDP、slide、WND时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure682::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure682::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure682::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_seq_in_window，Invalid param wnd。";
}

std::string UrmaFailure682::GetId() const
{
    return "urma_682";
}
} // namespace diag
