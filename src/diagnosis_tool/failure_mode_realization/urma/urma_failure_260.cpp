#include "urma_failure_260.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure260> g_urma("urma_260");

bool UrmaFailure260::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_seg") != std::string::npos &&
           message.find("[DRV_ERR]Failed to import seg, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure260::GetName() const
{
    return "下层注册或导入返回失败导致导入Segment失败";
}

std::string UrmaFailure260::GetRootCauseDesc() const
{
    return "urma_import_seg在导入Segment时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure260::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure260::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure260::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_seg，[DRV_ERR]Failed to import seg, dev_name:，, eid_idx:。";
}

std::string UrmaFailure260::GetId() const
{
    return "urma_260";
}
} // namespace diag
