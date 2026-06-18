#include "urma_failure_264.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure264> g_urma("urma_264");

bool UrmaFailure264::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unregister_seg") != std::string::npos &&
           message.find("[DRV_ERR]Unregister seg fail, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos && message.find(", tid:") != std::string::npos &&
           message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure264::GetName() const
{
    return "下层注册或导入返回失败导致注销Segment失败";
}

std::string UrmaFailure264::GetRootCauseDesc() const
{
    return "urma_unregister_seg在注销Segment时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure264::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure264::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure264::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unregister_seg，[DRV_ERR]Unregister seg fail, dev_name:，, "
           "eid_idx:，, tid:"
           "，, ret:。";
}

std::string UrmaFailure264::GetId() const
{
    return "urma_264";
}
} // namespace diag
