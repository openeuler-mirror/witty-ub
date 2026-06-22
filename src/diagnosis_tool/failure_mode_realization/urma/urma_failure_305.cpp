#include "urma_failure_305.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure305> g_urma("urma_305");

bool UrmaFailure305::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_register_health_check_task") != std::string::npos &&
           message.find("Failed to register health task: no valid route") != std::string::npos;
}

std::string UrmaFailure305::GetName() const
{
    return "下层注册或导入返回失败导致注册health、TASK失败";
}

std::string UrmaFailure305::GetRootCauseDesc() const
{
    return "bondp_register_health_check_"
           "task在注册health、TASK时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure305::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure305::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure305::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_register_health_check_task，Failed to register health task: no "
           "valid rou"
           "te。";
}

std::string UrmaFailure305::GetId() const
{
    return "urma_305";
}
} // namespace diag
