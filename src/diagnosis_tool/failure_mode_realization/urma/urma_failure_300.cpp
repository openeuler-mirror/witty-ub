#include "urma_failure_300.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure300> g_urma("urma_300");

bool UrmaFailure300::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_register_health_check_seg_for_jetty") != std::string::npos &&
           message.find("Failed to register health check segment") != std::string::npos;
}

std::string UrmaFailure300::GetName() const
{
    return "下层注册或导入返回失败导致注册health、Segment、FOR失败";
}

std::string UrmaFailure300::GetRootCauseDesc() const
{
    return "bondp_register_health_check_seg_for_"
           "jetty在注册health、Segment、FOR时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure300::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure300::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure300::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_health_check_seg_for_jetty，Failed to register health "
           "check seg"
           "ment。";
}

std::string UrmaFailure300::GetId() const
{
    return "urma_300";
}
} // namespace diag
