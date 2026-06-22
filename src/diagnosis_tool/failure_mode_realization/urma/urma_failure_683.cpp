#include "urma_failure_683.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure683> g_urma("urma_683");

bool UrmaFailure683::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_slide_wnd_seq_in_window") != std::string::npos &&
           message.find("Seq larger than total size of bitmap") != std::string::npos;
}

std::string UrmaFailure683::GetName() const
{
    return "BDP、slide、WND状态不满足要求导致bdpBDP、slide、WND失败";
}

std::string UrmaFailure683::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_seq_in_"
           "window执行bdpBDP、slide、WND时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure683::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure683::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure683::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_seq_in_window，Seq larger than total size of bitmap。";
}

std::string UrmaFailure683::GetId() const
{
    return "urma_683";
}
} // namespace diag
