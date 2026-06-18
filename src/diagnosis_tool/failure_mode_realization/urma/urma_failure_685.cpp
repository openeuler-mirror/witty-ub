#include "urma_failure_685.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure685> g_urma("urma_685");

bool UrmaFailure685::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_slide_wnd_has") != std::string::npos &&
           message.find("Seq larger than total size of bitmap") != std::string::npos;
}

std::string UrmaFailure685::GetName() const
{
    return "BDP、slide、WND状态不满足要求导致bdpBDP、slide、WND失败";
}

std::string UrmaFailure685::GetRootCauseDesc() const
{
    return "bdp_slide_wnd_has执行bdpBDP、slide、WND时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure685::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure685::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure685::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_slide_wnd_has，Seq larger than total size of bitmap。";
}

std::string UrmaFailure685::GetId() const
{
    return "urma_685";
}
} // namespace diag
