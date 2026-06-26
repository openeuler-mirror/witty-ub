#include "urma_failure_324.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure324> g_urma("urma_324");

bool UrmaFailure324::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_seg") != std::string::npos &&
           message.find("Failed to import pseg") != std::string::npos;
}

std::string UrmaFailure324::GetName() const
{
    return "下层注册或导入返回失败导致导入Segment失败";
}

std::string UrmaFailure324::GetRootCauseDesc() const
{
    return "bondp_import_seg在导入Segment时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure324::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure324::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure324::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_seg，Failed to import pseg。";
}

std::string UrmaFailure324::GetId() const
{
    return "urma_324";
}
} // namespace diag
