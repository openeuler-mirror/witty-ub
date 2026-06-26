#include "urma_failure_016.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure016> g_urma("urma_016");

bool UrmaFailure016::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_jfr") != std::string::npos &&
           message.find("Failed to init target active indices") != std::string::npos;
}

std::string UrmaFailure016::GetName() const
{
    return "下层查询返回失败导致导入JFR失败";
}

std::string UrmaFailure016::GetRootCauseDesc() const
{
    return "bondp_import_jfr需要从provider、驱动或缓存中获取JFR状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure016::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure016::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure016::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_jfr，Failed to init target active indices。";
}

std::string UrmaFailure016::GetId() const
{
    return "urma_016";
}
} // namespace diag
