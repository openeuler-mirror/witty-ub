#include "urma_failure_323.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure323> g_urma("urma_323");

bool UrmaFailure323::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_seg") != std::string::npos &&
           message.find("Failed to import vseg") != std::string::npos;
}

std::string UrmaFailure323::GetName() const
{
    return "下层注册或导入返回失败导致导入Segment失败";
}

std::string UrmaFailure323::GetRootCauseDesc() const
{
    return "bondp_import_seg在导入Segment时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure323::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure323::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure323::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_seg，Failed to import vseg。";
}

std::string UrmaFailure323::GetId() const
{
    return "urma_323";
}
} // namespace diag
