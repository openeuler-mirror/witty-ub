#include "urma_failure_296.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure296> g_urma("urma_296");

bool UrmaFailure296::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_pjfr") != std::string::npos &&
           message.find("Failed to import tjfr") != std::string::npos;
}

std::string UrmaFailure296::GetName() const
{
    return "下层注册或导入返回失败导致导入物理JFR失败";
}

std::string UrmaFailure296::GetRootCauseDesc() const
{
    return "bondp_import_pjfr在导入物理JFR时需要将对象登记到驱动或远端上下文，下层返回失败会阻断资源可见性建立。";
}

RootCause UrmaFailure296::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure296::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure296::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_pjfr，Failed to import tjfr。";
}

std::string UrmaFailure296::GetId() const
{
    return "urma_296";
}
} // namespace diag
