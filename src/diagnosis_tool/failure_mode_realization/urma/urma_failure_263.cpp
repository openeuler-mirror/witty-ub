#include "urma_failure_263.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure263> g_urma("urma_263");

bool UrmaFailure263::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_register_seg") != std::string::npos &&
           message.find("[DRV_ERR]register seg failed, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure263::GetName() const
{
    return "下层注册或导入返回失败导致注册Segment失败";
}

std::string UrmaFailure263::GetRootCauseDesc() const
{
    return "urma_register_seg在注册Segment时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure263::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure263::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure263::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_register_seg，[DRV_ERR]register seg failed, dev_name:，, "
           "eid_idx:。";
}

std::string UrmaFailure263::GetId() const
{
    return "urma_263";
}
} // namespace diag
